package com.demo;

import com.demo.BankAccount;
import org.junit.Assert;
import org.junit.Test;

public class BankAccount_isOverdrawn_Test_Normal_8 {


    @Test
    public void isOverdrawn_returnsExpectedStatusForNormalBalances() {
        BankAccount positive = new BankAccount("Alice", 100.0);
        Assert.assertFalse(positive.isOverdrawn());

        BankAccount negative = new BankAccount("Bob", -50.0);
        Assert.assertTrue(negative.isOverdrawn());

        BankAccount zero = new BankAccount("Carol", 0.0);
        Assert.assertFalse(zero.isOverdrawn());
    }

}
