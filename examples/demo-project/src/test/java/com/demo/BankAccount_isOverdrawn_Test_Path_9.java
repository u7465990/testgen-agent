package com.demo;

import com.demo.BankAccount;
import org.junit.Assert;
import org.junit.Test;

public class BankAccount_isOverdrawn_Test_Path_9 {


    @Test
    public void testIsOverdrawnCoversBothPaths() {
        BankAccount overdrawn = new BankAccount("Alice", -1.0);
        Assert.assertTrue("Negative balance should be considered overdrawn", overdrawn.isOverdrawn());

        BankAccount zeroBalance = new BankAccount("Bob", 0.0);
        Assert.assertFalse("Zero balance should not be considered overdrawn", zeroBalance.isOverdrawn());

        BankAccount positiveBalance = new BankAccount("Carol", 100.0);
        Assert.assertFalse("Positive balance should not be considered overdrawn", positiveBalance.isOverdrawn());
    }

}
