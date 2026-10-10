package com.demo;

import com.demo.BankAccount;
import org.junit.Assert;
import org.junit.Test;

public class BankAccount_isOverdrawn_Test_Path_9 {


    @Test
    public void testIsOverdrawnStatementCoverage() {
        BankAccount overdrawnAccount = new BankAccount("Alice", -100.0);
        boolean overdrawnResult = overdrawnAccount.isOverdrawn();
        Assert.assertTrue(overdrawnResult);

        BankAccount positiveAccount = new BankAccount("Bob", 250.0);
        boolean positiveResult = positiveAccount.isOverdrawn();
        Assert.assertFalse(positiveResult);

        BankAccount zeroAccount = new BankAccount("Carol", 0.0);
        boolean zeroResult = zeroAccount.isOverdrawn();
        Assert.assertFalse(zeroResult);
    }

}
